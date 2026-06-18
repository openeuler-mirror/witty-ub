#include "urma_failure_539.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure539> g_urma("urma_539");

bool UrmaFailure539::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfr_batch") != std::string::npos &&
           message.find("Failed to malloc buffer.") != std::string::npos;
}

std::string UrmaFailure539::GetName() const
{
    return "uint64分配失败导致删除JFR失败";
}

std::string UrmaFailure539::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfr_batch执行删除JFR前需要准备uint64，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure539::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure539::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure539::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfr_batch，Failed to malloc buffer.。";
}

std::string UrmaFailure539::GetId() const
{
    return "urma_539";
}
} // namespace diag
