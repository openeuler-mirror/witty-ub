#include "urma_failure_778.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure778> g_urma("urma_778");

bool UrmaFailure778::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_delete_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure778::GetName() const
{
    return "urma_delete_jfr 校验 JFR 无效导致删除流程拒绝继续执行";
}

std::string UrmaFailure778::GetRootCauseDesc() const
{
    return "urma_delete_jfr 在执行删除前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure778::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure778::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure778::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure778::GetId() const
{
    return "urma_778";
}

} // namespace diag
