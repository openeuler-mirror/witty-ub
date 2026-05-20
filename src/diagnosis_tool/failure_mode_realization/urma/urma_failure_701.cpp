#include "urma_failure_701.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure701> g_urma("urma_701");

bool UrmaFailure701::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_delete_pjfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete pjfr' | "
        "grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure701::GetName() const
{
    return "bondp_delete_pjfr 执行删除 JFR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure701::GetRootCauseDesc() const
{
    return "bondp_delete_pjfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure701::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure701::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure701::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to delete pjfr , ret";
}

std::string UrmaFailure701::GetId() const
{
    return "urma_701";
}

} // namespace diag
