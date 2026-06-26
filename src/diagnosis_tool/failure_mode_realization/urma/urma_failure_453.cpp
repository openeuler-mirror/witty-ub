#include "urma_failure_453.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure453> g_urma("urma_453");

bool UrmaFailure453::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfc_batch") != std::string::npos &&
           message.find("Failed to alloc memory.") != std::string::npos;
}

std::string UrmaFailure453::GetName() const
{
    return "urma context *分配失败导致删除JFC失败";
}

std::string UrmaFailure453::GetRootCauseDesc() const
{
    return "urma_delete_jfc_batch执行删除JFC前需要准备urma context *，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure453::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure453::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure453::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc_batch，Failed to alloc memory.。";
}

std::string UrmaFailure453::GetId() const
{
    return "urma_453";
}
} // namespace diag
