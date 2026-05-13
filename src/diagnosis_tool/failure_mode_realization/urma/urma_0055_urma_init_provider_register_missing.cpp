#include "urma_0055_urma_init_provider_register_missing.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0055UrmaInitProviderRegisterMissing> g_urma("urma_0055");

bool Urma0055UrmaInitProviderRegisterMissing::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"None of the providers registered."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0055UrmaInitProviderRegisterMissing::GetName() const
{
    return "urma_init provider注册缺失";
}

std::string Urma0055UrmaInitProviderRegisterMissing::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_FAIL";
}

RootCause Urma0055UrmaInitProviderRegisterMissing::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0055UrmaInitProviderRegisterMissing::GetFixSuggDesc() const
{
    return "查看/usr/lib64/urma目录下，是否存在liburma_udma.so等驱动文件，或查看文件是否具备x权限，完成正确部署后重试";
}

std::string Urma0055UrmaInitProviderRegisterMissing::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：None of the providers registered.";
}

std::string Urma0055UrmaInitProviderRegisterMissing::GetId() const
{
    return "urma_0055";
}
} // namespace diag
