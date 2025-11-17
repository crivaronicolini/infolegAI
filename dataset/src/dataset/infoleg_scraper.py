import asyncio
import csv
import re
from datetime import datetime
from typing import Optional, List
import logging

from dagster import ConfigurableResource
from pydantic import Field
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class InfolegClient(ConfigurableResource):
    """
    A Dagster resource for scraping legal norms from Argentina's Infoleg website.

    This resource provides methods to search for and scrape legal documents (`normas`)
    by date, handling batching, and rate limiting. It is designed to be used
    within Dagster assets to automate the collection of legal data.

    Attributes:
        daily_scrape_count (int): Maximum number of normas to scrape per day.
        batch_size (int): Number of concurrent requests per batch.
        delay_bw_batches (float): Seconds to wait between batches of requests.
    """

    daily_scrape_count: int = Field(
        default=200,
        description="Maximum number of normas to scrape per day.",
    )
    batch_size: int = Field(
        default=10,
        description="Number of concurrent requests per batch.",
    )
    delay_bw_batches: float = Field(
        default=3.0,
        description="Seconds to wait between batches.",
    )

    @staticmethod
    def convert_date_format(date_str: str) -> Optional[str]:
        """
        Convert date from DD-MMM-YYYY or DD/MM/YYYY to YYYY-MM-DD format.
        Handles Spanish month abbreviations.
        """
        if not date_str:
            return None

        # Try DD/MM/YYYY format first
        try:
            dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # Try DD-MMM-YYYY format with Spanish months
        month_map = {
            "ENE": "01",
            "FEB": "02",
            "MAR": "03",
            "ABR": "04",
            "MAY": "05",
            "JUN": "06",
            "JUL": "07",
            "AGO": "08",
            "SEP": "09",
            "OCT": "10",
            "NOV": "11",
            "DIC": "12",
            "ene": "01",
            "feb": "02",
            "mar": "03",
            "abr": "04",
            "may": "05",
            "jun": "06",
            "jul": "07",
            "ago": "08",
            "sep": "09",
            "oct": "10",
            "nov": "11",
            "dic": "12",
        }

        match = re.match(r"(\d{2})-([A-Za-z]{3})-(\d{4})", date_str.strip())
        if match:
            day, month_abbr, year = match.groups()
            month = month_map.get(month_abbr.upper())
            if month:
                return f"{year}-{month}-{day}"

        return None

    async def search_boletines(
        self,
        client: httpx.AsyncClient,
        boletin_fecha: str = "",
    ) -> List[int]:
        """
        Search for normas by Boletín Date.
        Returns a list of norma IDs found in the search results.

        Args:
            client: httpx AsyncClient instance
            boletin_number: Number of the Boletín Oficial (e.g., "35768")

        Returns:
            List of norma IDs found
        """
        # The actual boletín search URL
        search_url = "https://servicios.infoleg.gob.ar/infolegInternet/buscarBoletin.do"

        # Prepare form data for POST request
        # The radio button value determines search type:
        fecha = datetime.strptime(boletin_fecha, "%Y-%m-%d").date()
        form_data = {
            "buscarPorNro": "false",
            "diaPub": fecha.day,
            "mesPub": fecha.month,
            "anioPub": fecha.year,
        }
        boletin_number = boletin_fecha

        try:
            # Set headers to mimic browser request
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://servicios.infoleg.gob.ar/infolegInternet/mostrarBuscarBoletin.do",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

            # Make POST request to search
            response = await client.post(
                search_url, data=form_data, headers=headers, timeout=30.0, follow_redirects=True
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            norma_ids = []
            # print(soup.find_all("a", href=re.compile(r"verNorma\.do.*\?id=\d+")))
            # Find all links to verNorma.do with id parameter
            # Pattern: verNorma.do?id=XXXXXX
            for link in soup.find_all("a", href=re.compile(r"verNorma\.do.*\?id=\d+")):
                href = link.get("href")
                match = re.search(r"\?id=(\d+)", href)
                if match:
                    norma_id = int(match.group(1))
                    if norma_id not in norma_ids:
                        norma_ids.append(norma_id)

            # If no results found, check if we got any meaningful content
            if len(norma_ids) == 0:
                # Look for "no results" message or other indicators
                if "no se encontraron" in response.text.lower() or "sin resultados" in response.text.lower():
                    logger.warning(f"[Boletín {boletin_number}] No normas found in this boletín")
                else:
                    # Save response for debugging
                    # print(f"[Boletín {boletin_number}] No normas extracted. Response might need inspection.")
                    raise LookupError(
                        f"[Boletín {boletin_number}] No normas extracted. Response might need inspection."
                    )
                    # Save to file for debugging
                    # with open(f"debug_boletin_{boletin_number}.html", "w", encoding="utf-8") as f:
                    # f.write(response.text)
                    # logger.info(f"[Boletín {boletin_number}] Debug HTML saved to debug_boletin_{boletin_number}.html")
            else:
                logger.info(f"[Boletín {boletin_number}] Found {len(norma_ids)} normas")

            return norma_ids

        except httpx.HTTPStatusError as e:
            logger.exception(f"[Boletín {boletin_number}] HTTP error: {e.response.status_code}")
            return []
        except httpx.RequestError as e:
            logger.exception(f"[Boletín {boletin_number}] Request error: {e}")
            return []
        except Exception as e:
            logger.exception(f"[Boletín {boletin_number}] Unexpected error: {e}")
            return []

    async def scrape_norma_by_id(
        self,
        client: httpx.AsyncClient,
        norma_id: int,
    ) -> Optional[dict]:
        """
        Scrapes a single norma page from Infoleg and extracts all fields.
        Returns None if the page doesn't exist or has errors.
        """
        url = f"https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={norma_id}"

        try:
            response = await client.get(url, timeout=30.0)

            # Handle 404s gracefully
            if response.status_code == 404:
                logger.warning(f"[{norma_id}] Not found (404)")
                return None

            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Initialize data structure with all schema fields
            data = {
                "id_norma": norma_id,
                "tipo_norma": "",
                "numero_norma": "S/N",
                "clase_norma": "",
                "organismo_origen": "",
                "fecha_sancion": "",
                "numero_boletin": "",
                "fecha_boletin": "",
                "pagina_boletin": "",
                "titulo_resumido": "",
                "titulo_sumario": "",
                "texto_resumido": "",
                "observaciones": "",
                "texto_original": "",
                "texto_actualizado": "",
                "modificada_por": "0",
                "modifica_a": "0",
            }

            # Extract tipo_norma, numero_norma, clase_norma and organismo_origen from the first <strong> tag
            strong_tag = soup.find("strong")
            if strong_tag:
                # Get full text including inner elements
                strong_full_text = strong_tag.get_text(separator=" ", strip=True)

                # Clean up the text (remove multiple spaces, normalize)
                strong_full_text = re.sub(r"\s+", " ", strong_full_text)

                # Pattern: "TIPO_NORMA NUMERO/YEAR ORGANISMO" or "TIPO_NORMA NUMERO ORGANISMO"
                # Examples: "Disposición 47/2025 DIRECCION...", "Ley 26865 HONORABLE..."

                # Extract tipo_norma (first word(s) before the number)
                tipo_match = re.match(
                    r"^([A-ZÀÁÉÍÓÚÑa-zàáéíóúñ]+(?:\s+[A-ZÀÁÉÍÓÚÑa-zàáéíóúñ]+)*?)\s+\d+",
                    strong_full_text,
                )
                if tipo_match:
                    data["tipo_norma"] = tipo_match.group(1).strip()

                # Extract numero_norma - prioritize number without year
                # Pattern: extract just the number part before the slash if present
                numero_match = re.search(r"\b(\d+)(?:/\d{4})?\b", strong_full_text)
                if numero_match:
                    data["numero_norma"] = numero_match.group(1)

                # Extract organismo_origen - it's after the number/year
                # Split by the numero pattern and take what comes after
                organismo_match = re.search(r"\d+(?:/\d{4})?\s+(.+)", strong_full_text)
                if organismo_match:
                    data["organismo_origen"] = organismo_match.group(1).strip()

                # Extract clase_norma if present (e.g., "Conjunta", "A", "B", "C")
                # This would appear between tipo_norma and numero_norma
                if data["tipo_norma"]:
                    remaining = strong_full_text.replace(data["tipo_norma"], "", 1).strip()
                    if data["numero_norma"] != "S/N":
                        # Check if there's text between tipo and numero
                        clase_match = re.match(r"^([A-Za-z\s]+?)\s+\d+", remaining)
                        if clase_match:
                            clase = clase_match.group(1).strip()
                            if clase and not clase.isdigit():
                                data["clase_norma"] = clase

            # Extract fecha_sancion
            fecha_tag = soup.find("span", class_="vr_azul11")
            if fecha_tag:
                fecha_text = fecha_tag.get_text(strip=True)
                # Convert to YYYY-MM-DD format
                fecha_converted = self.convert_date_format(fecha_text)
                if fecha_converted:
                    data["fecha_sancion"] = fecha_converted
                else:
                    data["fecha_sancion"] = fecha_text

            # Extract titulo_resumido, titulo_sumario and boletin information
            h1_tag = soup.find("h1")
            if h1_tag:
                data["titulo_resumido"] = h1_tag.get_text(strip=True)

                # titulo_sumario: Look for <span class="destacado">
                destacado_span = soup.find("span", class_="destacado")
                if destacado_span:
                    data["titulo_sumario"] = destacado_span.get_text(strip=True)

                # Boletin info is in the next <p> tag
                p_boletin = h1_tag.find_next_sibling("p")
                if p_boletin:
                    boletin_text = p_boletin.get_text()

                    # Extract fecha_boletin (e.g., "01-ENE-2024" or as a link)
                    # First try to find it in a link
                    fecha_link = p_boletin.find("a", href=re.compile(r"page_id=216"))
                    if fecha_link:
                        fecha_text = fecha_link.get_text(strip=True)
                        # Convert to YYYY-MM-DD format
                        fecha_converted = self.convert_date_format(fecha_text)
                        if fecha_converted:
                            data["fecha_boletin"] = fecha_converted

                    # If not found in link, try regex
                    if not data["fecha_boletin"]:
                        fecha_match = re.search(r"(\d{2}-[A-Z]{3}-\d{4})", boletin_text)
                        if fecha_match:
                            fecha_converted = self.convert_date_format(fecha_match.group(1))
                            if fecha_converted:
                                data["fecha_boletin"] = fecha_converted

                    # Extract numero_boletin (handles encoding issues: Número or NÃºmero)
                    numero_match = re.search(r"N[uú]mero:\s*(\d+)", boletin_text)
                    if numero_match:
                        data["numero_boletin"] = numero_match.group(1)

                    # Extract pagina_boletin (handles encoding issues: Página or PÃ¡gina)
                    pagina_match = re.search(r"P[aá]gina:\s*(\d+)", boletin_text)
                    if pagina_match:
                        data["pagina_boletin"] = pagina_match.group(1)

            # Extract texto_resumido (summary after "Resumen:" label)
            # The summary can appear in several formats:
            # 1. Inside a <p> tag that contains a <strong>Resumen:</strong>
            # 2. Inside a <p> tag that starts with "Resumen:"

            # First, try to find <strong> containing "Resumen:" and get its parent
            resumen_strong = soup.find("strong", string=lambda x: x and "Resumen" in x)
            if resumen_strong and resumen_strong.parent:
                # Get the full text from the parent element
                parent_text = resumen_strong.parent.get_text(strip=True)
                # Remove the "Resumen:" label (with or without space)
                text = re.sub(r"^Resumen:\s*", "", parent_text, flags=re.IGNORECASE)
                if text and len(text) > 10:
                    data["texto_resumido"] = text

            # If still not found, look for <p> tag starting with "Resumen:"
            if not data["texto_resumido"]:
                for p_tag in soup.find_all("p"):
                    text = p_tag.get_text(strip=True)
                    if text.startswith("Resumen:") or text.startswith("resumen:"):
                        # Remove the "Resumen:" label
                        text = re.sub(r"^Resumen:\s*", "", text, flags=re.IGNORECASE)
                        if len(text) > 10:  # Make sure it's substantial
                            data["texto_resumido"] = text
                            break

            # Extract texto_original (link to original text)
            texto_link = soup.find("a", string=re.compile(r"Texto completo", re.IGNORECASE))
            if texto_link and texto_link.has_attr("href"):
                href = texto_link.get("href")
                if href:
                    # Handle relative URLs
                    if not href.startswith("http"):
                        data["texto_original"] = f"http://servicios.infoleg.gob.ar/infolegInternet/{href}"
                    else:
                        data["texto_original"] = href

            # Extract texto_actualizado (link to updated text)
            actualizado_link = soup.find("a", string=re.compile(r"Texto actualizado", re.IGNORECASE))
            if actualizado_link and actualizado_link.has_attr("href"):
                href = actualizado_link.get("href")
                if href:
                    if not href.startswith("http"):
                        data["texto_actualizado"] = f"http://servicios.infoleg.gob.ar/infolegInternet/{href}"
                    else:
                        data["texto_actualizado"] = href

            # Extract modifica_a (count of norms this one modifies)
            modifica_link = soup.find("a", href=re.compile(r"verVinculos\.do.*modo=1"))
            if modifica_link:
                link_text = modifica_link.get_text()
                count_match = re.search(r"(\d+)", link_text)
                if count_match:
                    data["modifica_a"] = count_match.group(1)

            # Extract modificada_por (count of norms that modify this one)
            modificada_link = soup.find("a", href=re.compile(r"verVinculos\.do.*modo=2"))
            if modificada_link:
                link_text = modificada_link.get_text()
                count_match = re.search(r"(\d+)", link_text)
                if count_match:
                    data["modificada_por"] = count_match.group(1)

            # Extract observaciones (if present)
            obs_strong = soup.find("strong", string=re.compile(r"Observaciones:", re.IGNORECASE))
            if obs_strong:
                next_node = obs_strong.next_sibling
                if next_node and isinstance(next_node, str):
                    data["observaciones"] = next_node.strip()

            logger.debug(
                f"[{norma_id}] ✓ {data['tipo_norma']} {data['numero_norma']} - {data['titulo_resumido'][:50] if data['titulo_resumido'] else 'NO TITLE'}"
            )
            return data

        except httpx.HTTPStatusError as e:
            logger.exception(f"[{norma_id}] HTTP error: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.exception(f"[{norma_id}] Request error: {e}")
            return None
        except Exception as e:
            logger.exception(f"[{norma_id}] Unexpected error: {e}")
            return None

    async def scrape_by_date(
        self,
        date: int,
        output_file: str,
        batch_size: Optional[int] = None,
        delay_between_batches: Optional[float] = None,
    ) -> int:
        """
        Scrape normas by searching the BO of a particular date.

        Args:
            date: searching date
            output_file: Path to output CSV file
            batch_size: Number of concurrent requests per batch. Defaults to resource config.
            delay_between_batches: Seconds to wait between batches. Defaults to resource config.

        Returns:
            Number of normas scraped
        """
        _batch_size = batch_size if batch_size is not None else self.batch_size
        _delay_between_batches = delay_between_batches if delay_between_batches is not None else self.delay_bw_batches
        # CSV schema fields
        fieldnames = [
            "id_norma",
            "tipo_norma",
            "numero_norma",
            "clase_norma",
            "organismo_origen",
            "fecha_sancion",
            "numero_boletin",
            "fecha_boletin",
            "pagina_boletin",
            "titulo_resumido",
            "titulo_sumario",
            "texto_resumido",
            "observaciones",
            "texto_original",
            "texto_actualizado",
            "modificada_por",
            "modifica_a",
        ]

        async with httpx.AsyncClient(follow_redirects=True) as client:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                total_scraped = 0
                all_norma_ids: list[int] = []

                # First, collect all norma IDs from all boletines
                logger.info(f"Searching boletines in date {date}...")
                norma_ids = await self.search_boletines(client, boletin_fecha=str(date))
                all_norma_ids.extend(norma_ids[: self.daily_scrape_count])
                # await asyncio.sleep(1)  # Rate limit between searches

                logger.info(f"\nFound {len(all_norma_ids)} total normas. Starting scraping...")

                # Now scrape all normas in batches
                tasks = []
                for i, norma_id in enumerate(all_norma_ids):
                    tasks.append(self.scrape_norma_by_id(client, norma_id))

                    # Process batch when full
                    if len(tasks) >= _batch_size:
                        results = await asyncio.gather(*tasks, return_exceptions=True)

                        for result in results:
                            if isinstance(result, dict):
                                writer.writerow(result)
                                total_scraped += 1

                        csvfile.flush()
                        tasks = []

                        # Rate limiting
                        if i < len(all_norma_ids) - 1:
                            await asyncio.sleep(_delay_between_batches)

                # Process remaining tasks
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, dict):
                            writer.writerow(result)
                            total_scraped += 1

        logger.info(f"\nCompleted! Scraped {total_scraped} normas from {len(all_norma_ids)} found.")
        return total_scraped

    async def cli_main(self):
        """
        Main function to scrape Infoleg normas and save to CSV.
        Supports both boletín-based search and legacy ID-based scraping.
        """
        import argparse

        parser = argparse.ArgumentParser(
            description="Scrape normas from Infoleg Argentina",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Scrape normas from Boletín range
  python resources.py --boletin-start 35690 --boletin-end 35695
            """,
        )

        parser.add_argument("--date", type=str, help="Boletin starting date")

        # Boletín-based scraping
        parser.add_argument("--boletin-start", type=int, help="Starting Boletín Oficial number")
        parser.add_argument("--boletin-end", type=int, help="Ending Boletín Oficial number (inclusive)")

        # Common parameters
        parser.add_argument(
            "--batch",
            type=int,
            default=10,
            dest="batch_size",
            help="Number of concurrent requests per batch (default: 10)",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=3.0,
            dest="delay_between_batches",
            help="Seconds to wait between batches (default: 3.0)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="infoleg_normativa_nacional_new.csv",
            help="Output CSV filename (default: infoleg_normativa_nacional_new.csv)",
        )

        args = parser.parse_args()

        # Boletín-based scraping (new mode)
        logger.info(f"Scraping normas from Boletín for {args.date}")
        await self.scrape_by_date(
            args.date,
            args.output,
            args.batch_size,
            args.delay_between_batches,
        )


if __name__ == "__main__":
    client = InfolegClient()
    asyncio.run(client.cli_main())
