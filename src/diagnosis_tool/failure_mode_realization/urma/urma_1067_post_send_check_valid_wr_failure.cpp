#include "urma_1067_post_send_check_valid_wr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1067PostSendCheckValidWrFailure> g_urma("urma_1067");

bool Urma1067PostSendCheckValidWrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Try to call post_send api by invalid comp_type: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1067PostSendCheckValidWrFailure::GetName() const
{
    return "post_send_check_valid 提交WR失败";
}

std::string Urma1067PostSendCheckValidWrFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bdp_send_comp->comp_type != BONDP_COMP_JFS && bdp_send_comp->comp_type != "
           "BONDP_COMP_JETTY`；该路径返回 URMA_EINVAL";
}

RootCause Urma1067PostSendCheckValidWrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1067PostSendCheckValidWrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1067PostSendCheckValidWrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Try to call post_send api by invalid comp_type: %";
}

std::string Urma1067PostSendCheckValidWrFailure::GetId() const
{
    return "urma_1067";
}
} // namespace diag
