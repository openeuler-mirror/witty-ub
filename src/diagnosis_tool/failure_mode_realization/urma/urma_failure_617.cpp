#include "urma_failure_617.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure617> g_urma("urma_617");

bool UrmaFailure617::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_rearm_jfc' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to rearm jfc: JFCE is NULL')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure617::GetName() const
{
    return "bondp_rearm_jfc 执行重挂 JFCE 失败导致当前资源状态无法推进";
}

std::string UrmaFailure617::GetRootCauseDesc() const
{
    return "bondp_rearm_jfc 调用下层 provider、bond 组件或系统接口处理 JFCE 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure617::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure617::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure617::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to rearm jfc: JFCE is NULL";
}

std::string UrmaFailure617::GetId() const
{
    return "urma_617";
}

} // namespace diag
