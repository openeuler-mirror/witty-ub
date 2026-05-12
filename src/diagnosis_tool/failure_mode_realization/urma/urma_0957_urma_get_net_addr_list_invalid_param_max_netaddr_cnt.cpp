#include "urma_0957_urma_get_net_addr_list_invalid_param_max_netaddr_cnt.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0957UrmaGetNetAddrListInvalidParamMaxNetaddrCnt> g_urma("urma_0957");

bool Urma0957UrmaGetNetAddrListInvalidParamMaxNetaddrCnt::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter with max_netaddr_cnt as 0."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0957UrmaGetNetAddrListInvalidParamMaxNetaddrCnt::GetName() const
{
    return "urma_get_net_addr_list 参数非法（max_netaddr_cnt == 0）";
}

std::string Urma0957UrmaGetNetAddrListInvalidParamMaxNetaddrCnt::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `max_netaddr_cnt == 0`；该路径返回 NULL";
}

RootCause Urma0957UrmaGetNetAddrListInvalidParamMaxNetaddrCnt::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0957UrmaGetNetAddrListInvalidParamMaxNetaddrCnt::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0957UrmaGetNetAddrListInvalidParamMaxNetaddrCnt::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter with max_netaddr_cnt as 0.";
}

std::string Urma0957UrmaGetNetAddrListInvalidParamMaxNetaddrCnt::GetId() const
{
    return "urma_0957";
}
} // namespace diag
