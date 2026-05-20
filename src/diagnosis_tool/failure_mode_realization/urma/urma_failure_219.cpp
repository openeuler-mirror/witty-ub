#include "urma_failure_219.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure219> g_urma("urma_219");

bool UrmaFailure219::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_comp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to get args list, type:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure219::GetName() const
{
    return "bondp_create_comp 执行创建 URMA 对象 失败导致当前资源状态无法推进";
}

std::string UrmaFailure219::GetRootCauseDesc() const
{
    return "bondp_create_comp 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure219::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure219::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure219::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to get args list, type";
}

std::string UrmaFailure219::GetId() const
{
    return "urma_219";
}

} // namespace diag
