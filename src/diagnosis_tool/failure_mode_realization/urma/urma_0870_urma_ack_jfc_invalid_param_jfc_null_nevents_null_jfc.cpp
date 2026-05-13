#include "urma_0870_urma_ack_jfc_invalid_param_jfc_null_nevents_null_jfc.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0870UrmaAckJfcInvalidParamJfcNullNeventsNullJfc> g_urma("urma_0870");

bool Urma0870UrmaAckJfcInvalidParamJfcNullNeventsNullJfc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0870UrmaAckJfcInvalidParamJfcNullNeventsNullJfc::GetName() const
{
    return "urma_ack_jfc 参数非法（jfc == NULL || nevents == NULL || jfc_cnt == 0）";
}

std::string Urma0870UrmaAckJfcInvalidParamJfcNullNeventsNullJfc::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL || nevents == NULL || jfc_cnt == 0`";
}

RootCause Urma0870UrmaAckJfcInvalidParamJfcNullNeventsNullJfc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0870UrmaAckJfcInvalidParamJfcNullNeventsNullJfc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0870UrmaAckJfcInvalidParamJfcNullNeventsNullJfc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0870UrmaAckJfcInvalidParamJfcNullNeventsNullJfc::GetId() const
{
    return "urma_0870";
}
} // namespace diag
