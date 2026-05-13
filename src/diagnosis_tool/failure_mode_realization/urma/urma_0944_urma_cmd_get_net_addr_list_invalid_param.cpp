#include "urma_0944_urma_cmd_get_net_addr_list_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0944UrmaCmdGetNetAddrListInvalidParam> g_urma("urma_0944");

bool Urma0944UrmaCmdGetNetAddrListInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0944UrmaCmdGetNetAddrListInvalidParam::GetName() const
{
    return "urma_cmd_get_net_addr_list 参数非法";
}

std::string Urma0944UrmaCmdGetNetAddrListInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || net_addr_info == NULL || cnt == NULL || "
           "max_netaddr_cnt == 0`；该路径返回 -EINVAL";
}

RootCause Urma0944UrmaCmdGetNetAddrListInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0944UrmaCmdGetNetAddrListInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0944UrmaCmdGetNetAddrListInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0944UrmaCmdGetNetAddrListInvalidParam::GetId() const
{
    return "urma_0944";
}
} // namespace diag
