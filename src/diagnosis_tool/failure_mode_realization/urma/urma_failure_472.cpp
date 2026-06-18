#include "urma_failure_472.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure472> g_urma("urma_472");

bool UrmaFailure472::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jfc") != std::string::npos &&
           message.find("Failed to exec ops->deactive_jfc.") != std::string::npos;
}

std::string UrmaFailure472::GetName() const
{
    return "去激活JFC执行失败导致去激活JFC失败";
}

std::string UrmaFailure472::GetRootCauseDesc() const
{
    return "urma_deactive_jfc执行去激活JFC时依赖的去激活JFC步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure472::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure472::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure472::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfc，Failed to exec ops->deactive_jfc.。";
}

std::string UrmaFailure472::GetId() const
{
    return "urma_472";
}
} // namespace diag
