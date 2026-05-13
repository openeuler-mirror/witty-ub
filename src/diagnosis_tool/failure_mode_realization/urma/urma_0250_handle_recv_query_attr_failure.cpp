#include "urma_0250_handle_recv_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0250HandleRecvQueryAttrFailure> g_urma("urma_0250");

bool Urma0250HandleRecvQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get target jetty id"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0250HandleRecvQueryAttrFailure::GetName() const
{
    return "handle_recv 查询属性失败";
}

std::string Urma0250HandleRecvQueryAttrFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret != 0`；该路径返回 CR_HANDLER_ERR_AND_COPY";
}

RootCause Urma0250HandleRecvQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0250HandleRecvQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0250HandleRecvQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get target jetty id";
}

std::string Urma0250HandleRecvQueryAttrFailure::GetId() const
{
    return "urma_0250";
}
} // namespace diag
