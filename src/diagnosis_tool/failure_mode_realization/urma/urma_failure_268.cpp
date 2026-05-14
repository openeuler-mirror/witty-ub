#include "urma_failure_268.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure268> g_urma("urma_268");

bool UrmaFailure268::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_set_aggr_mode' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'bonding context is invalid in user ctl')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure268::GetName() const
{
    return "bondp_set_aggr_mode 校验 context 无效导致设置流程拒绝继续执行";
}

std::string UrmaFailure268::GetRootCauseDesc() const
{
    return "bondp_set_aggr_mode 在执行设置前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure268::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure268::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure268::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：bonding context is invalid in user ctl";
}

std::string UrmaFailure268::GetId() const
{
    return "urma_268";
}

} // namespace diag
