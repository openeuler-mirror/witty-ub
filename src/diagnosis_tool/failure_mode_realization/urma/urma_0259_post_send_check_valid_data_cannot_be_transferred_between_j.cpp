#include "urma_0259_post_send_check_valid_data_cannot_be_transferred_between_j.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0259PostSendCheckValidDataCannotBeTransferredBetweenJ> g_urma("urma_0259");

bool Urma0259PostSendCheckValidDataCannotBeTransferredBetweenJ::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "Data cannot be transferred between jettys in different matrix server mode"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0259PostSendCheckValidDataCannotBeTransferredBetweenJ::GetName() const
{
    return "post_send_check_valid Data cannot be transferred between j（is_in_matrix_server(bdp_send_comp->bondp_ctx) "
           "!= bdp_tjetty->is_in_matrix_server）";
}

std::string Urma0259PostSendCheckValidDataCannotBeTransferredBetweenJ::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `is_in_matrix_server(bdp_send_comp->bondp_ctx) != "
           "bdp_tjetty->is_in_matrix_server`；该路径返回 URMA_EINVAL";
}

RootCause Urma0259PostSendCheckValidDataCannotBeTransferredBetweenJ::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0259PostSendCheckValidDataCannotBeTransferredBetweenJ::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0259PostSendCheckValidDataCannotBeTransferredBetweenJ::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Data cannot be transferred between jettys in different matrix "
           "server mode";
}

std::string Urma0259PostSendCheckValidDataCannotBeTransferredBetweenJ::GetId() const
{
    return "urma_0259";
}
} // namespace diag
