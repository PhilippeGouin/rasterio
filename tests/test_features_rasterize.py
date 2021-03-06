import logging
import sys
import numpy
import pytest

import rasterio
from rasterio.features import shapes, rasterize, geometry_mask


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_rasterize_geometries():
    """
    Make sure that geometries are correctly rasterized according to parameters
    """

    rows = cols = 10
    transform = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    geometry = {
        'type': 'Polygon',
        'coordinates': [[(2, 2), (2, 4.25), (4.25, 4.25), (4.25, 2), (2, 2)]]
    }

    with rasterio.drivers():
        # we expect a subset of the pixels using default mode
        result = rasterize([geometry], out_shape=(rows, cols))
        truth = numpy.zeros((rows, cols))
        truth[2:4, 2:4] = 1
        assert numpy.array_equal(result, truth)

        out = numpy.zeros((rows, cols))
        result = rasterize([geometry], out=out, default_value=1)
        assert numpy.array_equal(out, truth)

        # we expect all touched pixels
        result = rasterize(
            [geometry], out_shape=(rows, cols), all_touched=True
        )
        truth = numpy.zeros((rows, cols))
        truth[2:5, 2:5] = 1
        assert numpy.array_equal(result, truth)

        # we expect the pixel value to match the one we pass in
        value = 5
        result = rasterize([(geometry, value)], out_shape=(rows, cols))
        truth = numpy.zeros((rows, cols))
        truth[2:4, 2:4] = value
        assert numpy.array_equal(result, truth)

        # Check the fill and default transform.
        # we expect the pixel value to match the one we pass in
        value = 5
        result = rasterize(
            [(geometry, value)],
            out_shape=(rows, cols),
            fill=1
        )
        truth = numpy.ones((rows, cols))
        truth[2:4, 2:4] = value
        assert numpy.array_equal(result, truth)


def test_rasterize_dtype():
    """Make sure that data types are handled correctly"""

    rows = cols = 10
    transform = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    geometry = {
        'type': 'Polygon',
        'coordinates': [[(2, 2), (2, 4.25), (4.25, 4.25), (4.25, 2), (2, 2)]]
    }

    with rasterio.drivers():
        # Supported types should all work properly
        supported_types = (
            ('int16', -32768),
            ('int32', -2147483648),
            ('uint8', 255),
            ('uint16', 65535),
            ('uint32', 4294967295),
            ('float32', 1.434532),
            ('float64', -98332.133422114)
        )

        for dtype, default_value in supported_types:
            truth = numpy.zeros((rows, cols), dtype=dtype)
            truth[2:4, 2:4] = default_value

            result = rasterize(
                [geometry],
                out_shape=(rows, cols),
                default_value=default_value,
                dtype=dtype
            )
            assert numpy.array_equal(result, truth)
            assert numpy.dtype(result.dtype) == numpy.dtype(truth.dtype)

            result = rasterize(
                [(geometry, default_value)],
                out_shape=(rows, cols)
            )
            if numpy.dtype(dtype).kind == 'f':
                assert numpy.allclose(result, truth)
            else:
                assert numpy.array_equal(result, truth)
            # Since dtype is auto-detected, it may not match due to upcasting

        # Unsupported types should all raise exceptions
        unsupported_types = (
            ('int8', -127),
            ('int64', 20439845334323),
            ('float16', -9343.232)
        )

        for dtype, default_value in unsupported_types:
            with pytest.raises(ValueError):
                rasterize(
                    [geometry],
                    out_shape=(rows, cols),
                    default_value=default_value,
                    dtype=dtype
                )

            with pytest.raises(ValueError):
                rasterize(
                    [(geometry, default_value)],
                    out_shape=(rows, cols),
                    dtype=dtype
                )

        # Mismatched values and dtypes should raise exceptions
        mismatched_types = (('uint8', 3.2423), ('uint8', -2147483648))
        for dtype, default_value in mismatched_types:
            with pytest.raises(ValueError):
                rasterize(
                    [geometry],
                    out_shape=(rows, cols),
                    default_value=default_value,
                    dtype=dtype
                )

            with pytest.raises(ValueError):
                rasterize(
                    [(geometry, default_value)],
                    out_shape=(rows, cols),
                    dtype=dtype
                )


def test_rasterize_geometries_symmetric():
    """Make sure that rasterize is symmetric with shapes"""

    rows = cols = 10
    transform = (1.0, 0.0, 0.0, 0.0, -1.0, 0.0)
    truth = numpy.zeros((rows, cols), dtype=rasterio.ubyte)
    truth[2:5, 2:5] = 1
    with rasterio.drivers():
        s = shapes(truth, transform=transform)
        result = rasterize(s, out_shape=(rows, cols), transform=transform)
        assert numpy.array_equal(result, truth)


def test_geometry_mask():
    rows = cols = 10
    transform = (1.0, 0.0, 0.0, 0.0, -1.0, 0.0)
    truth = numpy.zeros((rows, cols), dtype=rasterio.bool_)
    truth[2:5, 2:5] = True
    with rasterio.drivers():
        s = shapes((truth * 10).astype(rasterio.ubyte), transform=transform)
        # Strip out values returned from shapes, and only keep first shape
        geoms = [next(s)[0]]

        # Regular mask should be the inverse of truth raster
        mask = geometry_mask(geoms, out_shape=(rows, cols), transform=transform)
        assert numpy.array_equal(mask, numpy.invert(truth))

        # Inverted mask should be the same as the truth raster
        mask = geometry_mask(geoms, out_shape=(rows, cols), transform=transform,
                             invert=True)
        assert numpy.array_equal(mask, truth)