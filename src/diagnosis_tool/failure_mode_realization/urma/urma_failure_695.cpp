#include "urma_failure_695.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure695> g_urma("urma_695");

bool UrmaFailure695::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_delete_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete vjfc'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure695::GetName() const
{
    return "bondp_delete_jfc 执行删除 JFC 失败导致当前资源状态无法推进";
}

std::string UrmaFailure695::GetRootCauseDesc() const
{
    return "bondp_delete_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure695::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure695::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure695::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to delete vjfc";
}

std::string UrmaFailure695::GetId() const
{
    return "urma_695";
}

} // namespace diag
