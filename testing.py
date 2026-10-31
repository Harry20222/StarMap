import astropy.units as u  # ensuring standard unit to represent custom lengths
import matplotlib.pyplot as plt  # plotting
from astropy.coordinates import SkyCoord  # Celestial coordinate repr. interface
from astropy.io import fits  # FITS file opener, knowledge extractor and manipulator
from astropy.wcs import WCS  # World Coordinate System wrapper and manipulator
from astroquery.gaia import Gaia  # To Query Gaia data releases
from astroquery.mast import (
    Observations,
)  # Downloading observations/images from MAST via astroquery
from astroquery.vizier import Vizier  # To query catalogs in VizieR

print(Observations.list_missions())