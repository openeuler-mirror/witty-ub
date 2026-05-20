#include "urma_failure_649.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure649> g_urma("urma_649");

bool UrmaFailure649::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'post_recv_check_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid bdp_comp'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure649::GetName() const
{
    return "post_recv_check_valid 校验 URMA 对象 无效导致投递流程拒绝继续执行";
}

std::string UrmaFailure649::GetRootCauseDesc() const
{
    return "post_recv_check_valid 在执行投递前发现调用方传入的 URMA 对象 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure649::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure649::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure649::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid bdp_comp";
}

std::string UrmaFailure649::GetId() const
{
    return "urma_649";
}

} // namespace diag
