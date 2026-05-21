#include "urma_failure_902.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure902> g_urma("urma_902");

bool UrmaFailure902::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_advise_jfr_async' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure902::GetName() const
{
    return "urma_advise_jfr_async 校验 context 无效导致处理流程拒绝继续执行";
}

std::string UrmaFailure902::GetRootCauseDesc() const
{
    return "urma_advise_jfr_async 在执行处理前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure902::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure902::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure902::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure902::GetId() const
{
    return "urma_902";
}

} // namespace diag
