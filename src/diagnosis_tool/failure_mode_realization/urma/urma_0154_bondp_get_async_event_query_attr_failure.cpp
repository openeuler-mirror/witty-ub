#include "urma_0154_bondp_get_async_event_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0154BondpGetAsyncEventQueryAttrFailure> g_urma("urma_0154");

bool Urma0154BondpGetAsyncEventQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"failed to get invalid jetty."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0154BondpGetAsyncEventQueryAttrFailure::GetName() const
{
    return "bondp_get_async_event 查询属性失败";
}

std::string Urma0154BondpGetAsyncEventQueryAttrFailure::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0154BondpGetAsyncEventQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0154BondpGetAsyncEventQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0154BondpGetAsyncEventQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：failed to get invalid jetty.";
}

std::string Urma0154BondpGetAsyncEventQueryAttrFailure::GetId() const
{
    return "urma_0154";
}
} // namespace diag
