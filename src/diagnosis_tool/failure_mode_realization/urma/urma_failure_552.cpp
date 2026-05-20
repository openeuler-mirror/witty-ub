#include "urma_failure_552.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure552> g_urma("urma_552");

bool UrmaFailure552::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_getenv_log_level' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter: log level str'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure552::GetName() const
{
    return "urma_getenv_log_level 校验 URMA 对象 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure552::GetRootCauseDesc() const
{
    return "urma_getenv_log_level 在执行获取前发现调用方传入的 URMA 对象 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure552::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure552::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure552::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter: log level str";
}

std::string UrmaFailure552::GetId() const
{
    return "urma_552";
}

} // namespace diag
