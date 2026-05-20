#include "urma_failure_644.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure644> g_urma("urma_644");

bool UrmaFailure644::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'post_send_check_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'All bonding devs are invalid'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure644::GetName() const
{
    return "post_send_check_valid 校验 context 无效导致投递流程拒绝继续执行";
}

std::string UrmaFailure644::GetRootCauseDesc() const
{
    return "post_send_check_valid 在执行投递前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure644::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure644::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure644::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：All bonding devs are invalid";
}

std::string UrmaFailure644::GetId() const
{
    return "urma_644";
}

} // namespace diag
