#include "urma_0763_urma_free_jfc_resource_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0763UrmaFreeJfcResourceFailure> g_urma("urma_0763");

bool Urma0763UrmaFreeJfcResourceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfc still actived, please deactived first"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0763UrmaFreeJfcResourceFailure::GetName() const
{
    return "urma_free_jfc 激活资源失败";
}

std::string Urma0763UrmaFreeJfcResourceFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0763UrmaFreeJfcResourceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0763UrmaFreeJfcResourceFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0763UrmaFreeJfcResourceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfc still actived, please deactived first";
}

std::string Urma0763UrmaFreeJfcResourceFailure::GetId() const
{
    return "urma_0763";
}
} // namespace diag
