#include "urma_failure_711.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure711> g_urma("urma_711");

bool UrmaFailure711::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_delete_comp_jfce' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to delete p_jfce, ret =')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure711::GetName() const
{
    return "bondp_delete_comp_jfce 执行删除 JFCE 失败导致当前资源状态无法推进";
}

std::string UrmaFailure711::GetRootCauseDesc() const
{
    return "bondp_delete_comp_jfce 调用下层 provider、bond 组件或系统接口处理 JFCE 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure711::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure711::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure711::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to delete p_jfce, ret =";
}

std::string UrmaFailure711::GetId() const
{
    return "urma_711";
}

} // namespace diag
