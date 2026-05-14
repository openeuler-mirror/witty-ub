#include "urma_failure_857.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure857> g_urma("urma_857");

bool UrmaFailure857::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bdp_slide_wnd_seq_in_window' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Seq larger than total size of bitmap')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure857::GetName() const
{
    return "bdp_slide_wnd_seq_in_window 更新 URMA 对象 映射结构失败导致资源索引不可用";
}

std::string UrmaFailure857::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_seq_in_window 需要维护 URMA 对象 "
           "到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。";
}

RootCause UrmaFailure857::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure857::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure857::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Seq larger than total size of bitmap";
}

std::string UrmaFailure857::GetId() const
{
    return "urma_857";
}

} // namespace diag
