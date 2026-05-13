#include "urma_0343_urma_cmd_ack_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0343UrmaCmdAckJfcInvalidParam> g_urma("urma_0343");

bool Urma0343UrmaCmdAckJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0343UrmaCmdAckJfcInvalidParam::GetName() const
{
    return "urma_cmd_ack_jfc 参数非法";
}

std::string Urma0343UrmaCmdAckJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL || nevents == NULL || jfc_cnt == 0`";
}

RootCause Urma0343UrmaCmdAckJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0343UrmaCmdAckJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0343UrmaCmdAckJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0343UrmaCmdAckJfcInvalidParam::GetId() const
{
    return "urma_0343";
}
} // namespace diag
