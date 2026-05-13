#include "urma_1068_post_send_check_valid_all_bonding_devs_are_invalid.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1068PostSendCheckValidAllBondingDevsAreInvalid> g_urma("urma_1068");

bool Urma1068PostSendCheckValidAllBondingDevsAreInvalid::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"All bonding devs are invalid"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1068PostSendCheckValidAllBondingDevsAreInvalid::GetName() const
{
    return "post_send_check_valid All bonding devs are invalid";
}

std::string Urma1068PostSendCheckValidAllBondingDevsAreInvalid::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `is_all_pjetty_fail(bjetty_ctx)`；该路径返回 URMA_FAIL";
}

RootCause Urma1068PostSendCheckValidAllBondingDevsAreInvalid::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1068PostSendCheckValidAllBondingDevsAreInvalid::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1068PostSendCheckValidAllBondingDevsAreInvalid::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：All bonding devs are invalid";
}

std::string Urma1068PostSendCheckValidAllBondingDevsAreInvalid::GetId() const
{
    return "urma_1068";
}
} // namespace diag
