#include "urma_failure_751.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure751> g_urma("urma_751");

bool UrmaFailure751::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_delete_jetty_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure751::GetName() const
{
    return "urma_cmd_delete_jetty_batch 校验 context 无效导致删除流程拒绝继续执行";
}

std::string UrmaFailure751::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jetty_batch 在执行删除前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure751::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure751::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure751::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter, index";
}

std::string UrmaFailure751::GetId() const
{
    return "urma_751";
}

} // namespace diag
