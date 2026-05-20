#include "urma_failure_263.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure263> g_urma("urma_263");

bool UrmaFailure263::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_context' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Uninitialized variables'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure263::GetName() const
{
    return "bondp_create_context 执行创建 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure263::GetRootCauseDesc() const
{
    return "bondp_create_context 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure263::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure263::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure263::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Uninitialized variables";
}

std::string UrmaFailure263::GetId() const
{
    return "urma_263";
}

} // namespace diag
