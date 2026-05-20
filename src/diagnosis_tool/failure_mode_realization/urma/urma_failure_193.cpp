#include "urma_failure_193.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure193> g_urma("urma_193");

bool UrmaFailure193::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid well known jetty id:' | "
        "grep -F ', should be in (0, 1024)'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure193::GetName() const
{
    return "bondp_create_jetty 校验 Jetty 无效导致创建流程拒绝继续执行";
}

std::string UrmaFailure193::GetRootCauseDesc() const
{
    return "bondp_create_jetty 在执行创建前发现调用方传入的 Jetty 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure193::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure193::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure193::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid well known jetty id: , should be in (0, 1024)";
}

std::string UrmaFailure193::GetId() const
{
    return "urma_193";
}

} // namespace diag
