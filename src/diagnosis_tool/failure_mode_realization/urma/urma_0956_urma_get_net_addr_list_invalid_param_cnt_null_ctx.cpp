#include "urma_0956_urma_get_net_addr_list_invalid_param_cnt_null_ctx.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0956UrmaGetNetAddrListInvalidParamCntNullCtx> g_urma("urma_0956");

bool Urma0956UrmaGetNetAddrListInvalidParamCntNullCtx::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0956UrmaGetNetAddrListInvalidParamCntNullCtx::GetName() const
{
    return "urma_get_net_addr_list 参数非法（cnt == NULL || ctx == NULL || ctx->dev == NULL || ctx->dev->sysfs_dev == "
           "NULL）";
}

std::string Urma0956UrmaGetNetAddrListInvalidParamCntNullCtx::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `cnt == NULL || ctx == NULL || ctx->dev == NULL || ctx->dev->sysfs_dev == "
           "NULL`；该路径返回 NULL";
}

RootCause Urma0956UrmaGetNetAddrListInvalidParamCntNullCtx::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0956UrmaGetNetAddrListInvalidParamCntNullCtx::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0956UrmaGetNetAddrListInvalidParamCntNullCtx::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0956UrmaGetNetAddrListInvalidParamCntNullCtx::GetId() const
{
    return "urma_0956";
}
} // namespace diag
