#include "urma_1119_urma_send_invalid_param_flag_bs_inline_flag_urma_inline.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1119UrmaSendInvalidParamFlagBsInlineFlagUrmaInline> g_urma("urma_1119");

bool Urma1119UrmaSendInvalidParamFlagBsInlineFlagUrmaInline::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1119UrmaSendInvalidParamFlagBsInlineFlagUrmaInline::GetName() const
{
    return "urma_send 参数非法（flag.bs.inline_flag == URMA_INLINE_DISABLE && src_tseg == NULL）";
}

std::string Urma1119UrmaSendInvalidParamFlagBsInlineFlagUrmaInline::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `flag.bs.inline_flag == URMA_INLINE_DISABLE && src_tseg == NULL`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma1119UrmaSendInvalidParamFlagBsInlineFlagUrmaInline::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1119UrmaSendInvalidParamFlagBsInlineFlagUrmaInline::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1119UrmaSendInvalidParamFlagBsInlineFlagUrmaInline::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1119UrmaSendInvalidParamFlagBsInlineFlagUrmaInline::GetId() const
{
    return "urma_1119";
}
} // namespace diag
