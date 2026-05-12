#include "urma_0621_urma_alloc_jfc_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0621UrmaAllocJfcResourceAllocFailure> g_urma("urma_0621");

bool Urma0621UrmaAllocJfcResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"failed to exec ops->alloc_jfc"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0621UrmaAllocJfcResourceAllocFailure::GetName() const
{
    return "urma_alloc_jfc 分配资源失败";
}

std::string Urma0621UrmaAllocJfcResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 status == URMA_SUCCESS ? URMA_ENOMEM "
           ": s";
}

RootCause Urma0621UrmaAllocJfcResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0621UrmaAllocJfcResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0621UrmaAllocJfcResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：failed to exec ops->alloc_jfc";
}

std::string Urma0621UrmaAllocJfcResourceAllocFailure::GetId() const
{
    return "urma_0621";
}
} // namespace diag
