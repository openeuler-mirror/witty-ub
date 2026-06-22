#include "urma_failure_406.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure406> g_urma("urma_406");

bool UrmaFailure406::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jfs_opt") != std::string::npos &&
           message.find("jfc not exist in jfs.") != std::string::npos;
}

std::string UrmaFailure406::GetName() const
{
    return "JFS状态不满足要求导致设置JFS失败";
}

std::string UrmaFailure406::GetRootCauseDesc() const
{
    return "urma_cmd_set_jfs_opt执行设置JFS时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure406::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure406::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure406::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jfs_opt，jfc not exist in jfs.。";
}

std::string UrmaFailure406::GetId() const
{
    return "urma_406";
}
} // namespace diag
