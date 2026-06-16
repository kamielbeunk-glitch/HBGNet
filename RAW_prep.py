" Code prepares raw data into train_image, train_mask, test_image, test_mask folders."


from pdb import main

from osgeo import gdal, ogr
import numpy as np

def rasterize_polygons(polygon_path, output_tif, RGB_image):
    """Rasterize vector polygons to binary mask matching reference image"""
    
    # Open reference image to get dimensions
    ref_ds = gdal.Open(RGB_image)
    width = ref_ds.RasterXSize
    height = ref_ds.RasterYSize
    geotrans = ref_ds.GetGeoTransform()
    proj = ref_ds.GetProjection()
    
    # Create empty raster
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(output_tif, width, height, 1, gdal.GDT_Byte)
    out_ds.SetGeoTransform(geotrans)
    out_ds.SetProjection(proj)
    
    # Open vector file
    vec_ds = ogr.Open(polygon_path)
    layer = vec_ds.GetLayer()
    
    # Rasterize: polygons = 255, background = 0
    gdal.RasterizeLayer(out_ds, [1], layer, burn_values=[255])
    
    del out_ds
    del ref_ds



def join_rasters(raster1_path, raster2_path, output_path):  
    " Joins RGB image with an additional band (mask) into a single multi-band raster"
    "RGB must be the first raster!"
    # Open the first raster (RGB image)
    raster1_ds = gdal.Open(raster1_path)
    raster1_band_count = raster1_ds.RasterCount
    raster1_geotransform = raster1_ds.GetGeoTransform()
    raster1_projection = raster1_ds.GetProjection()
    # Open the second raster (mask)
    raster2_ds = gdal.Open(raster2_path)
    raster2_band_count = raster2_ds.RasterCount
    # Use raster1's dimensions and geotransform for the output
    width = raster1_ds.RasterXSize
    height = raster1_ds.RasterYSize
    # Create output raster with 4 bands (3 for RGB + 1 for mask)
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(output_path, width, height, raster1_band_count + raster2_band_count, gdal.GDT_Byte)
    out_ds.SetGeoTransform(raster1_geotransform)
    out_ds.SetProjection(raster1_projection)
    # Copy RGB bands from raster1
    for i in range(1, raster1_band_count + 1):
        band = raster1_ds.GetRasterBand(i)
        data = band.ReadAsArray()
        out_band = out_ds.GetRasterBand(i)
        out_band.WriteArray(data)
        out_band.FlushCache()
    # Copy mask band from raster2 to the last band of output
    mask_band = raster2_ds.GetRasterBand(1)
    mask_data = mask_band.ReadAsArray()
    out_band = out_ds.GetRasterBand(raster1_band_count + 1)
    out_band.WriteArray(mask_data)
    out_band.FlushCache()
    # Clean up
    del out_ds
    del raster1_ds
    del raster2_ds



def RAW_prepper(input_raster, output_RGB_folder, output_mask_folder):

    "This function tiles a raster into 512*512 patches, all other sizes are discarded "
    "Then it separates RGB and mask into different folders"
    raster = gdal.Open(input_raster)
    # Tile into 512*512 patches
    # Get raster dimensions and geotransform
    width = raster.RasterXSize
    height = raster.RasterYSize
    geotrans = raster.GetGeoTransform()
    # Calculate number of tiles in x and y directions
    tile_size = 512
    x_tiles = (width + tile_size - 1) // tile_size
    y_tiles = (height + tile_size - 1) // tile_size
    # Loop through tiles and save as separate files
    filenumber = 0
    for i in range(x_tiles):
        for j in range(y_tiles):
            filenumber += 1
            x_offset = i * tile_size
            y_offset = j * tile_size
            x_size = min(tile_size, width - x_offset)
            y_size = min(tile_size, height - y_offset)
            if x_size < tile_size or y_size < tile_size:
                continue  # Skip tiles smaller than 512x512
            tile_data = raster.ReadAsArray(x_offset, y_offset, x_size, y_size)

            # Continue if any pixel in band 1 has a 0 value 
            if np.any(tile_data == raster.GetRasterBand(1).GetNoDataValue()):
                continue

            # Create output file name
            output_RGB_file = f"{output_RGB_folder}/{filenumber:03d}.tif"
            output_mask_file = f"{output_mask_folder}/{filenumber:03d}.tif"

            # Save RGB tile 
            driver = gdal.GetDriverByName("GTiff")
            out_rgb = driver.Create(output_RGB_file, x_size, y_size, raster.RasterCount - 2, gdal.GDT_Byte)
            out_rgb.SetGeoTransform((
                geotrans[0] + x_offset * geotrans[1],
                geotrans[1],
                0,
                geotrans[3] + y_offset * geotrans[5],
                0,
                geotrans[5]
            ))
            out_rgb.SetProjection(raster.GetProjection())
            for band in range(raster.RasterCount - 2):
                out_band = out_rgb.GetRasterBand(band + 1)
                out_band.WriteArray(tile_data[band])
                out_band.FlushCache()

            # Save mask tile (last band)
            out_mask = driver.Create(output_mask_file, x_size, y_size, 1, gdal.GDT_Byte)
            out_mask.SetGeoTransform((
                geotrans[0] + x_offset * geotrans[1],
                geotrans[1],
                0,
                geotrans[3] + y_offset * geotrans[5],
                0,
                geotrans[5]
            ))
            out_mask.SetProjection(raster.GetProjection())
            mask_band = out_mask.GetRasterBand(1)
            mask_band.WriteArray(tile_data[-1])
            mask_band.FlushCache()

            del out_rgb
            del out_mask



if __name__ == "__main__":
    "Run these functions for all the required AOIs and separate them into train and test folders"
    # Rasterize train and test dataset polygons to create binary masks
    rasterize_polygons(polygon_path=r"./RAW/RAWPolygon/ParcelPolygons2.gpkg",
                   output_tif=r"./RAW/RAWMask/AOI_2_mask.tif",
                   RGB_image=r"./RAW/RAWImage/AOI_2.tif")
    
    # rasterize_polygons(polygon_path=r"./RAW/RAWPolygon/ParcelPolygons3.gpkg",
    #                output_tif=r"./RAW/RAWMask/AOI_3_mask.tif",
    #                RGB_image=r"./RAW/RAWImage/AOI_3.tif")

    # Join RGB to mask 
    join_rasters(raster1_path=r"./RAW/RAWImage/AOI_2.tif",
                    raster2_path=r"./RAW/RAWMask/AOI_2_mask.tif",
                    output_path=r"./RAW/RAWImage/AOI_2_joined.tif")
    
    # join_rasters(raster1_path=r"./RAW/RAWImage/AOI_3.tif",
    #                 raster2_path=r"./RAW/RAWMask/AOI_3_mask.tif",
    #                 output_path=r"./RAW/RAWImage/AOI_3_joined.tif")

    # Tile and save separate RGB and mask into different folders 
    RAW_prepper(input_raster=r"./RAW/RAWImage/AOI_2_joined.tif",
           output_RGB_folder=r"./inputs/train/train_image",
           output_mask_folder=r"./inputs/train/train_mask")
    
    # RAW_prepper(input_raster=r"./RAW/RAWImage/AOI_3_joined.tif",
    #        output_RGB_folder=r"./inputs/test/train_image",
    #        output_mask_folder=r"./inputs/test/train_mask")