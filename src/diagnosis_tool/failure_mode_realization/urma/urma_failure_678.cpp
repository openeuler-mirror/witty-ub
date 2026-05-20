#include "urma_failure_678.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure678> g_urma("urma_678");

bool UrmaFailure678::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_send' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'null pointer exists in tjfr'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure678::GetName() const
{
    return "urma_send 校验 JFR 无效导致发送流程拒绝继续执行";
}

std::string UrmaFailure678::GetRootCauseDesc() const
{
    return "urma_send 在执行发送前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure678::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure678::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure678::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：null pointer exists in tjfr";
}

std::string UrmaFailure678::GetId() const
{
    return "urma_678";
}

} // namespace diag
