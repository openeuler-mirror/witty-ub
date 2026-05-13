#include "urma_0260_post_send_check_valid_data_cannot_be_transferred_between_j.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0260PostSendCheckValidDataCannotBeTransferredBetweenJ> g_urma("urma_0260");

bool Urma0260PostSendCheckValidDataCannotBeTransferredBetweenJ::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Data cannot be transferred between jettys in different multipath mode"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0260PostSendCheckValidDataCannotBeTransferredBetweenJ::GetName() const
{
    return "post_send_check_valid Data cannot be transferred between j（is_multipath_comp(bdp_send_comp) != "
           "bdp_tjetty->is_multipath）";
}

std::string Urma0260PostSendCheckValidDataCannotBeTransferredBetweenJ::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `is_multipath_comp(bdp_send_comp) != bdp_tjetty->is_multipath`；该路径返回 URMA_EINVAL";
}

RootCause Urma0260PostSendCheckValidDataCannotBeTransferredBetweenJ::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0260PostSendCheckValidDataCannotBeTransferredBetweenJ::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0260PostSendCheckValidDataCannotBeTransferredBetweenJ::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Data cannot be transferred between jettys in different multipath "
           "mode";
}

std::string Urma0260PostSendCheckValidDataCannotBeTransferredBetweenJ::GetId() const
{
    return "urma_0260";
}
} // namespace diag
