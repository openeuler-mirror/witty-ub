#include "urma_failure_578.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure578> g_urma("urma_578");

bool UrmaFailure578::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfr_batch") != std::string::npos &&
           message.find("Failed to alloc memory.") != std::string::npos;
}

std::string UrmaFailure578::GetName() const
{
    return "urma context *分配失败导致删除JFR失败";
}

std::string UrmaFailure578::GetRootCauseDesc() const
{
    return "urma_delete_jfr_batch执行删除JFR前需要准备urma context *，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure578::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure578::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure578::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr_batch，Failed to alloc memory.。";
}

std::string UrmaFailure578::GetId() const
{
    return "urma_578";
}
} // namespace diag
