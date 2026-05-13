#include "urma_0500_urma_cmd_get_tp_list_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0500UrmaCmdGetTpListInvalidParam> g_urma("urma_0500");

bool Urma0500UrmaCmdGetTpListInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0500UrmaCmdGetTpListInvalidParam::GetName() const
{
    return "urma_cmd_get_tp_list 参数非法";
}

std::string Urma0500UrmaCmdGetTpListInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || cfg == NULL || tp_cnt == NULL || *tp_cnt > "
           "URMA_CMD_MAX_TP_NUM || `；该路径返回 URMA_EINVAL";
}

RootCause Urma0500UrmaCmdGetTpListInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0500UrmaCmdGetTpListInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0500UrmaCmdGetTpListInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0500UrmaCmdGetTpListInvalidParam::GetId() const
{
    return "urma_0500";
}
} // namespace diag
