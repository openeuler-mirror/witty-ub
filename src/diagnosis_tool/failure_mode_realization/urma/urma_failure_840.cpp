#include "urma_failure_840.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure840> g_urma("urma_840");

bool UrmaFailure840::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_modify_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'modify pjfr fail, index:' | "
        "grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure840::GetName() const
{
    return "bondp_modify_jfr 执行修改 JFR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure840::GetRootCauseDesc() const
{
    return "bondp_modify_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure840::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure840::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure840::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：modify pjfr fail, index:, ret";
}

std::string UrmaFailure840::GetId() const
{
    return "urma_840";
}

} // namespace diag
