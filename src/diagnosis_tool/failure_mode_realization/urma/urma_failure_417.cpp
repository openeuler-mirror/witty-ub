#include "urma_failure_417.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure417> g_urma("urma_417");

bool UrmaFailure417::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfc_batch") != std::string::npos &&
           message.find("Failed to malloc buffer.") != std::string::npos;
}

std::string UrmaFailure417::GetName() const
{
    return "uint64分配失败导致删除JFC失败";
}

std::string UrmaFailure417::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfc_batch执行删除JFC前需要准备uint64，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure417::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure417::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure417::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc_batch，Failed to malloc buffer.。";
}

std::string UrmaFailure417::GetId() const
{
    return "urma_417";
}
} // namespace diag
