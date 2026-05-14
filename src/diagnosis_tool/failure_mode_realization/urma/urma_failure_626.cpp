#include "urma_failure_626.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure626> g_urma("urma_626");

bool UrmaFailure626::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'comp_post_send' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid post jfs wr type')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure626::GetName() const
{
    return "comp_post_send 校验 context 无效导致投递流程拒绝继续执行";
}

std::string UrmaFailure626::GetRootCauseDesc() const
{
    return "comp_post_send 在执行投递前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure626::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure626::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure626::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid post jfs wr type";
}

std::string UrmaFailure626::GetId() const
{
    return "urma_626";
}

} // namespace diag
