#include "urma_0767_urma_free_jfr_resource_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0767UrmaFreeJfrResourceFailure> g_urma("urma_0767");

bool Urma0767UrmaFreeJfrResourceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to free jfr."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0767UrmaFreeJfrResourceFailure::GetName() const
{
    return "urma_free_jfr 释放资源失败";
}

std::string Urma0767UrmaFreeJfrResourceFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma0767UrmaFreeJfrResourceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0767UrmaFreeJfrResourceFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0767UrmaFreeJfrResourceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to free jfr.";
}

std::string Urma0767UrmaFreeJfrResourceFailure::GetId() const
{
    return "urma_0767";
}
} // namespace diag
