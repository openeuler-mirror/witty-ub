#include "urma_failure_774.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure774> g_urma("urma_774");

bool UrmaFailure774::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_free_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure774::GetName() const
{
    return "urma_free_jfr 校验 JFR 无效导致释放流程拒绝继续执行";
}

std::string UrmaFailure774::GetRootCauseDesc() const
{
    return "urma_free_jfr 在执行释放前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure774::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure774::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure774::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure774::GetId() const
{
    return "urma_774";
}

} // namespace diag
