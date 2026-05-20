#include "urma_failure_689.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure689> g_urma("urma_689");

bool UrmaFailure689::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_post_jfr_wr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure689::GetName() const
{
    return "urma_post_jfr_wr 校验 JFR 无效导致投递流程拒绝继续执行";
}

std::string UrmaFailure689::GetRootCauseDesc() const
{
    return "urma_post_jfr_wr 在执行投递前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure689::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure689::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure689::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure689::GetId() const
{
    return "urma_689";
}

} // namespace diag
