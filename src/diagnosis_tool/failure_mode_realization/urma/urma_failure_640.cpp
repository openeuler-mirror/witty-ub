#include "urma_failure_640.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure640> g_urma("urma_640");

bool UrmaFailure640::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'post_send_check_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid bdp_target_jetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure640::GetName() const
{
    return "post_send_check_valid 校验 目标 Jetty 无效导致投递流程拒绝继续执行";
}

std::string UrmaFailure640::GetRootCauseDesc() const
{
    return "post_send_check_valid 在执行投递前发现调用方传入的 目标 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure640::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure640::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure640::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid bdp_target_jetty";
}

std::string UrmaFailure640::GetId() const
{
    return "urma_640";
}

} // namespace diag
