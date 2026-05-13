#include "urma_0666_urma_create_jetty_grp_resource_alloc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0666UrmaCreateJettyGrpResourceAllocFailure> g_urma("urma_0666");

bool Urma0666UrmaCreateJettyGrpResourceAllocFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"alloc jetty list failed."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0666UrmaCreateJettyGrpResourceAllocFailure::GetName() const
{
    return "urma_create_jetty_grp 分配资源失败";
}

std::string Urma0666UrmaCreateJettyGrpResourceAllocFailure::GetRootCauseDesc() const
{
    return "资源分配失败，可能由于内存不足或 fd/对象数量达到规格限制；该路径返回 NULL";
}

RootCause Urma0666UrmaCreateJettyGrpResourceAllocFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0666UrmaCreateJettyGrpResourceAllocFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0666UrmaCreateJettyGrpResourceAllocFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：alloc jetty list failed.";
}

std::string Urma0666UrmaCreateJettyGrpResourceAllocFailure::GetId() const
{
    return "urma_0666";
}
} // namespace diag
