#include "urma_failure_022.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure022> g_urma("urma_022");

bool UrmaFailure022::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_global_ctx_init") != std::string::npos &&
           message.find("Failed to alloc global context") != std::string::npos;
}

std::string UrmaFailure022::GetName() const
{
    return "bondp global context分配失败导致初始化global、context失败";
}

std::string UrmaFailure022::GetRootCauseDesc() const
{
    return "bondp_global_ctx_init执行初始化global、context前需要准备bondp global "
           "context，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure022::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure022::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure022::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_global_ctx_init，Failed to alloc global context。";
}

std::string UrmaFailure022::GetId() const
{
    return "urma_022";
}
} // namespace diag
