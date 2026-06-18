#include "urma_failure_390.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure390> g_urma("urma_390");

bool UrmaFailure390::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_post_recv_wr_and_store") != std::string::npos &&
           message.find("Failed to post recv wr") != std::string::npos;
}

std::string UrmaFailure390::GetName() const
{
    return "数据通路操作返回失败导致投递工作请求、AND、store失败";
}

std::string UrmaFailure390::GetRootCauseDesc() const
{
    return "bondp_post_recv_wr_and_"
           "store执行数据收发相关操作时，下层队列、完成队列或provider返回错误，导致请求无法正常提交或回收。";
}

RootCause UrmaFailure390::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure390::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure390::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_post_recv_wr_and_store，Failed to post recv wr。";
}

std::string UrmaFailure390::GetId() const
{
    return "urma_390";
}
} // namespace diag
