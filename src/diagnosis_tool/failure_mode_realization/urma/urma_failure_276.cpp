#include "urma_failure_276.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure276> g_urma("urma_276");

bool UrmaFailure276::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_register_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create vseg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure276::GetName() const
{
    return "bondp_register_seg 执行注册 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure276::GetRootCauseDesc() const
{
    return "bondp_register_seg 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure276::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure276::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure276::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to create vseg";
}

std::string UrmaFailure276::GetId() const
{
    return "urma_276";
}

} // namespace diag
