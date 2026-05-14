#include "urma_failure_477.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure477> g_urma("urma_477");

bool UrmaFailure477::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_log_set_thread_tag' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure477::GetName() const
{
    return "urma_log_set_thread_tag 校验 URMA 对象 无效导致读取流程拒绝继续执行";
}

std::string UrmaFailure477::GetRootCauseDesc() const
{
    return "urma_log_set_thread_tag 在执行读取前发现调用方传入的 URMA 对象 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure477::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure477::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure477::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure477::GetId() const
{
    return "urma_477";
}

} // namespace diag
