import torch
import torch.nn.functional as func
from torch import nn

# most parameters in pytorch modules are torch.float32 by default
_kernel = torch.tensor([[0.0010],
                        [0.0076],
                        [0.0360],
                        [0.1094],
                        [0.2130],
                        [0.2660],
                        [0.2130],
                        [0.1094],
                        [0.0360],
                        [0.0076],
                        [0.0010]], dtype=torch.float32)
_window = torch.mm(_kernel, _kernel.T)
_c1 = (0.01 * 255) ** 2
_c2 = (0.03 * 255) ** 2


# def mySSIM(img, img2, **kwargs):
#     """
#     Ref:
#     Image quality assessment: From error visibility to structural similarity

#     The results are the same as that of the official released MATLAB code in
#     https://ece.uwaterloo.ca/~z70wang/research/ssim/.

#     For three-channel images, SSIM is calculated for each channel and then
#     averaged.

#     Args:
#         img (Tensor): Images with range [0, 1], shape (n, 3/1, h, w).
#         img2 (Tensor): Images with range [0, 1], shape (n, 3/1, h, w).

#     Returns:
#         float: SSIM result.
#     """

#     assert img.shape == img2.shape, (f'Image shapes are different: {img.shape}, {img2.shape}.')

#     img = img.to(torch.float64)
#     img2 = img2.to(torch.float64)

#     ssim = _ssim(img * 255., img2 * 255.)
#     return ssim

def ssim(img, img2):
    """
    Args:
        img (Tensor): Images with range [0, 255], shape (n, 3/1, h, w).
        img2 (Tensor): Images with range [0, 255], shape (n, 3/1, h, w).

    Returns:
        float: SSIM result.
    """

    "Generated Gaussian Kernel, shape (11, 1.5)"

    window = torch.mm(_kernel, _kernel.T)
    window = window.view(1, 1, 11, 11).expand(img.size(1), 1, 11, 11).to(img.dtype).to(img.device)

    mu1 = func.conv2d(img, window, stride=1, padding=0, groups=img.shape[1])
    mu2 = func.conv2d(img2, window, stride=1, padding=0, groups=img2.shape[1])
    mu1_sq = mu1.pow(2)
    mu2_sq = mu2.pow(2)
    mu1_mu2 = mu1 * mu2
    sigma1_sq = func.conv2d(img * img, window, stride=1, padding=0, groups=img.shape[1]) - mu1_sq
    sigma2_sq = func.conv2d(img2 * img2, window, stride=1, padding=0, groups=img.shape[1]) - mu2_sq
    sigma12 = func.conv2d(img * img2, window, stride=1, padding=0, groups=img.shape[1]) - mu1_mu2

    cs_map = (2 * sigma12 + _c2) / (sigma1_sq + sigma2_sq + _c2)
    ssim_map = ((2 * mu1_mu2 + _c1) / (mu1_sq + mu2_sq + _c1)) * cs_map
    return ssim_map.mean([1, 2, 3])

class SSIMLoss(nn.Module):
    def __init__(self, dtype=torch.float32):
        super(SSIMLoss, self).__init__()
        # register kernel as buffer
        self.register_buffer( 'window', _window.view(1, 1, 11, 11).expand(1,1,11,11).to(dtype) )

    def _ssim(self, img, img2):
        """
        Args:
            img (Tensor): Images with range [0, 255], shape (n, 3/1, h, w).
            img2 (Tensor): Images with range [0, 255], shape (n, 3/1, h, w).

        Returns:
            float: SSIM result.
        """
        window = self.window.expand(img.size(1), -1, -1, -1).to(img.device)

        mu1 = func.conv2d(img, window, stride=1, padding=0, groups=img.shape[1])
        mu2 = func.conv2d(img2, window, stride=1, padding=0, groups=img2.shape[1])
        mu1_sq = mu1.pow(2)
        mu2_sq = mu2.pow(2)
        mu1_mu2 = mu1 * mu2
        sigma1_sq = func.conv2d(img * img, window, stride=1, padding=0, groups=img.shape[1]) - mu1_sq
        sigma2_sq = func.conv2d(img2 * img2, window, stride=1, padding=0, groups=img.shape[1]) - mu2_sq
        sigma12 = func.conv2d(img * img2, window, stride=1, padding=0, groups=img.shape[1]) - mu1_mu2

        cs_map = (2 * sigma12 + _c2) / (sigma1_sq + sigma2_sq + _c2)
        ssim_map = ((2 * mu1_mu2 + _c1) / (mu1_sq + mu2_sq + _c1)) * cs_map
        return ssim_map.mean([1, 2, 3])

    def forward(self, img, img2):
        assert img.shape == img2.shape, (f'Image shapes are different: {img.shape}, {img2.shape}.')
        return 1 - self._ssim(img, img2)
