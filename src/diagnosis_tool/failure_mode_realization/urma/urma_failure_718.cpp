#include "urma_failure_718.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure718> g_urma("urma_718");

bool UrmaFailure718::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_delete_vseg' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'invalid param')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure718::GetName() const
{
    return "bondp_delete_vseg 校验 segment 无效导致删除流程拒绝继续执行";
}

std::string UrmaFailure718::GetRootCauseDesc() const
{
    return "bondp_delete_vseg 在执行删除前发现调用方传入的 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure718::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure718::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure718::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：invalid param";
}

std::string UrmaFailure718::GetId() const
{
    return "urma_718";
}

} // namespace diag
