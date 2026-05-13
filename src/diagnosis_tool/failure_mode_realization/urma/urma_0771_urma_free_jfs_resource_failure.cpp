#include "urma_0771_urma_free_jfs_resource_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0771UrmaFreeJfsResourceFailure> g_urma("urma_0771");

bool Urma0771UrmaFreeJfsResourceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to free jfs."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0771UrmaFreeJfsResourceFailure::GetName() const
{
    return "urma_free_jfs 释放资源失败";
}

std::string Urma0771UrmaFreeJfsResourceFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma0771UrmaFreeJfsResourceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0771UrmaFreeJfsResourceFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0771UrmaFreeJfsResourceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to free jfs.";
}

std::string Urma0771UrmaFreeJfsResourceFailure::GetId() const
{
    return "urma_0771";
}
} // namespace diag
