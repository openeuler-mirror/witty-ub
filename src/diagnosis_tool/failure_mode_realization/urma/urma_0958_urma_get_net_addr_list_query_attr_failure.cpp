#include "urma_0958_urma_get_net_addr_list_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0958UrmaGetNetAddrListQueryAttrFailure> g_urma("urma_0958");

bool Urma0958UrmaGetNetAddrListQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get netaddr list, ret: %, max_netaddr_cnt: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0958UrmaGetNetAddrListQueryAttrFailure::GetName() const
{
    return "urma_get_net_addr_list 查询属性失败";
}

std::string Urma0958UrmaGetNetAddrListQueryAttrFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret < 0`；该路径返回 NULL";
}

RootCause Urma0958UrmaGetNetAddrListQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0958UrmaGetNetAddrListQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0958UrmaGetNetAddrListQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get netaddr list, ret: %, max_netaddr_cnt: %.";
}

std::string Urma0958UrmaGetNetAddrListQueryAttrFailure::GetId() const
{
    return "urma_0958";
}
} // namespace diag
