#include "urma_failure_612.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure612> g_urma("urma_612");

bool UrmaFailure612::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_unregister_seg' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure612::GetName() const
{
    return "urma_unregister_seg 校验 context 无效导致注册流程拒绝继续执行";
}

std::string UrmaFailure612::GetRootCauseDesc() const
{
    return "urma_unregister_seg 在执行注册前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure612::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure612::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure612::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure612::GetId() const
{
    return "urma_612";
}

} // namespace diag
