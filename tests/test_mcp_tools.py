from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_email_server.app import (
    add_email_account,
    create_draft,
    delete_emails,
    download_attachment,
    get_emails_content,
    list_available_accounts,
    list_emails_metadata,
    send_email,
)
from mcp_email_server.config import EmailServer, EmailSettings, ProviderSettings
from mcp_email_server.emails.models import (
    AttachmentDownloadResponse,
    EmailBodyResponse,
    EmailContentBatchResponse,
    EmailMetadata,
    EmailMetadataPageResponse,
)


class TestMcpTools:
    @pytest.mark.asyncio
    async def test_list_available_accounts(self):
        """Test list_available_accounts MCP tool."""
        # Create test accounts
        email_settings = EmailSettings(
            account_name="test_email",
            full_name="Test User",
            email_address="test@example.com",
            incoming=EmailServer(
                user_name="test_user",
                password="test_password",
                host="imap.example.com",
                port=993,
                use_ssl=True,
            ),
            outgoing=EmailServer(
                user_name="test_user",
                password="test_password",
                host="smtp.example.com",
                port=465,
                use_ssl=True,
            ),
        )

        provider_settings = ProviderSettings(
            account_name="test_provider",
            provider_name="test",
            api_key="test_key",
        )

        # Mock the get_settings function
        mock_settings = MagicMock()
        mock_settings.get_accounts.return_value = [email_settings, provider_settings]

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            # Call the function
            result = await list_available_accounts()

            # Verify the result
            assert len(result) == 2
            assert result[0].account_name == "test_email"
            assert result[1].account_name == "test_provider"

            # Verify get_accounts was called correctly
            mock_settings.get_accounts.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_email_account(self):
        """Test add_email_account MCP tool."""
        # Create test email settings
        email_settings = EmailSettings(
            account_name="test_account",
            full_name="Test User",
            email_address="test@example.com",
            incoming=EmailServer(
                user_name="test_user",
                password="test_password",
                host="imap.example.com",
                port=993,
                use_ssl=True,
            ),
            outgoing=EmailServer(
                user_name="test_user",
                password="test_password",
                host="smtp.example.com",
                port=465,
                use_ssl=True,
            ),
        )

        # Mock the get_settings function
        mock_settings = MagicMock()

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            # Call the function
            result = await add_email_account(email_settings)

            # Verify the return value
            assert result == "Successfully added email account 'test_account'"

            # Verify add_email and store were called correctly
            mock_settings.add_email.assert_called_once_with(email_settings)
            mock_settings.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_emails_metadata(self):
        """Test list_emails_metadata MCP tool."""
        # Create test data
        now = datetime.now(timezone.utc)
        email_metadata = EmailMetadata(
            email_id="12345",
            subject="Test Subject",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            date=now,
            attachments=[],
        )

        email_metadata_page = EmailMetadataPageResponse(
            page=1,
            page_size=10,
            before=now,
            since=None,
            subject="Test",
            emails=[email_metadata],
            total=1,
        )

        # Mock the dispatch_handler function
        mock_handler = AsyncMock()
        mock_handler.get_emails_metadata.return_value = email_metadata_page

        with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
            # Call the function
            result = await list_emails_metadata(
                account_name="test_account",
                page=1,
                page_size=10,
                before=now,
                since=None,
                subject="Test",
                from_address="sender@example.com",
                to_address=None,
            )

            # Verify the result
            assert result == email_metadata_page
            assert result.page == 1
            assert result.page_size == 10
            assert result.before == now
            assert result.subject == "Test"
            assert len(result.emails) == 1
            assert result.emails[0].subject == "Test Subject"
            assert result.emails[0].email_id == "12345"

            # Verify dispatch_handler and get_emails_metadata were called correctly
            mock_handler.get_emails_metadata.assert_called_once_with(
                page=1,
                page_size=10,
                before=now,
                since=None,
                subject="Test",
                from_address="sender@example.com",
                to_address=None,
                order="desc",
                mailbox="INBOX",
                seen=None,
                flagged=None,
                answered=None,
            )

    @pytest.mark.asyncio
    async def test_list_emails_metadata_with_mailbox(self):
        """Test list_emails_metadata MCP tool with custom mailbox."""
        now = datetime.now(timezone.utc)
        email_metadata = EmailMetadata(
            email_id="12345",
            subject="Sent Subject",
            sender="me@example.com",
            recipients=["recipient@example.com"],
            date=now,
            attachments=[],
        )

        email_metadata_page = EmailMetadataPageResponse(
            page=1,
            page_size=10,
            before=None,
            since=None,
            subject=None,
            emails=[email_metadata],
            total=1,
        )

        mock_handler = AsyncMock()
        mock_handler.get_emails_metadata.return_value = email_metadata_page

        with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
            result = await list_emails_metadata(
                account_name="test_account",
                mailbox="Sent",
            )

            assert result == email_metadata_page
            mock_handler.get_emails_metadata.assert_called_once_with(
                page=1,
                page_size=10,
                before=None,
                since=None,
                subject=None,
                from_address=None,
                to_address=None,
                order="desc",
                mailbox="Sent",
                seen=None,
                flagged=None,
                answered=None,
            )

    @pytest.mark.asyncio
    async def test_get_emails_content_single(self):
        """Test get_emails_content MCP tool with single email."""
        # Create test data
        now = datetime.now(timezone.utc)
        email_body = EmailBodyResponse(
            email_id="12345",
            subject="Test Subject",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            date=now,
            body="This is the test email body content.",
            attachments=["attachment1.pdf"],
        )

        batch_response = EmailContentBatchResponse(
            emails=[email_body],
            requested_count=1,
            retrieved_count=1,
            failed_ids=[],
        )

        # Mock the dispatch_handler function
        mock_handler = AsyncMock()
        mock_handler.get_emails_content.return_value = batch_response

        with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
            # Call the function
            result = await get_emails_content(
                account_name="test_account",
                email_ids=["12345"],
            )

            # Verify the result
            assert result == batch_response
            assert result.requested_count == 1
            assert result.retrieved_count == 1
            assert len(result.failed_ids) == 0
            assert len(result.emails) == 1
            assert result.emails[0].email_id == "12345"
            assert result.emails[0].subject == "Test Subject"

            # Verify dispatch_handler and get_emails_content were called correctly
            mock_handler.get_emails_content.assert_called_once_with(["12345"], "INBOX")

    @pytest.mark.asyncio
    async def test_get_emails_content_batch(self):
        """Test get_emails_content MCP tool with multiple emails."""
        # Create test data
        now = datetime.now(timezone.utc)
        email1 = EmailBodyResponse(
            email_id="12345",
            subject="Test Subject 1",
            sender="sender1@example.com",
            recipients=["recipient@example.com"],
            date=now,
            body="This is the first test email body content.",
            attachments=[],
        )

        email2 = EmailBodyResponse(
            email_id="12346",
            subject="Test Subject 2",
            sender="sender2@example.com",
            recipients=["recipient@example.com"],
            date=now,
            body="This is the second test email body content.",
            attachments=["attachment1.pdf"],
        )

        batch_response = EmailContentBatchResponse(
            emails=[email1, email2],
            requested_count=3,
            retrieved_count=2,
            failed_ids=["12347"],
        )

        # Mock the dispatch_handler function
        mock_handler = AsyncMock()
        mock_handler.get_emails_content.return_value = batch_response

        with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
            # Call the function
            result = await get_emails_content(
                account_name="test_account",
                email_ids=["12345", "12346", "12347"],
            )

            # Verify the result
            assert result == batch_response
            assert result.requested_count == 3
            assert result.retrieved_count == 2
            assert len(result.failed_ids) == 1
            assert result.failed_ids[0] == "12347"
            assert len(result.emails) == 2
            assert result.emails[0].email_id == "12345"
            assert result.emails[1].email_id == "12346"

            # Verify dispatch_handler and get_emails_content were called correctly
            mock_handler.get_emails_content.assert_called_once_with(["12345", "12346", "12347"], "INBOX")

    @pytest.mark.asyncio
    async def test_get_emails_content_with_mailbox(self):
        """Test get_emails_content MCP tool with custom mailbox."""
        now = datetime.now(timezone.utc)
        email_body = EmailBodyResponse(
            email_id="12345",
            subject="Sent Subject",
            sender="me@example.com",
            recipients=["recipient@example.com"],
            date=now,
            body="This is a sent email.",
            attachments=[],
        )

        batch_response = EmailContentBatchResponse(
            emails=[email_body],
            requested_count=1,
            retrieved_count=1,
            failed_ids=[],
        )

        mock_handler = AsyncMock()
        mock_handler.get_emails_content.return_value = batch_response

        with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
            result = await get_emails_content(
                account_name="test_account",
                email_ids=["12345"],
                mailbox="Sent",
            )

            assert result == batch_response
            mock_handler.get_emails_content.assert_called_once_with(["12345"], "Sent")

    @pytest.mark.asyncio
    async def test_send_email(self):
        """Test send_email MCP tool."""
        mock_settings = MagicMock()
        mock_settings.read_only = False

        # Mock the dispatch_handler function
        mock_handler = AsyncMock()

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
                # Call the function
                result = await send_email(
                    account_name="test_account",
                    recipients=["recipient@example.com"],
                    subject="Test Subject",
                    body="Test Body",
                    cc=["cc@example.com"],
                    bcc=["bcc@example.com"],
                )

                # Verify the return value
                assert result == "Email sent successfully to recipient@example.com"

                # Verify send_email was called correctly
                mock_handler.send_email.assert_called_once_with(
                    ["recipient@example.com"],
                    "Test Subject",
                    "Test Body",
                    ["cc@example.com"],
                    ["bcc@example.com"],
                    False,
                    None,
                    None,  # in_reply_to
                    None,  # references
                )

    @pytest.mark.asyncio
    async def test_delete_emails(self):
        """Test delete_emails MCP tool."""
        mock_settings = MagicMock()
        mock_settings.read_only = False

        mock_handler = AsyncMock()
        mock_handler.delete_emails.return_value = (["12345", "12346"], [])

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
                result = await delete_emails(
                    account_name="test_account",
                    email_ids=["12345", "12346"],
                )

                assert result == "Successfully deleted 2 email(s)"
                mock_handler.delete_emails.assert_called_once_with(["12345", "12346"], "INBOX")

    @pytest.mark.asyncio
    async def test_delete_emails_with_failures(self):
        """Test delete_emails MCP tool with some failures."""
        mock_settings = MagicMock()
        mock_settings.read_only = False

        mock_handler = AsyncMock()
        mock_handler.delete_emails.return_value = (["12345"], ["12346", "12347"])

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
                result = await delete_emails(
                    account_name="test_account",
                    email_ids=["12345", "12346", "12347"],
                )

                assert result == "Successfully deleted 1 email(s), failed to delete 2 email(s): 12346, 12347"
                mock_handler.delete_emails.assert_called_once_with(["12345", "12346", "12347"], "INBOX")

    @pytest.mark.asyncio
    async def test_delete_emails_with_mailbox(self):
        """Test delete_emails MCP tool with custom mailbox."""
        mock_settings = MagicMock()
        mock_settings.read_only = False

        mock_handler = AsyncMock()
        mock_handler.delete_emails.return_value = (["12345"], [])

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
                result = await delete_emails(
                    account_name="test_account",
                    email_ids=["12345"],
                    mailbox="Trash",
                )

                assert result == "Successfully deleted 1 email(s)"
                mock_handler.delete_emails.assert_called_once_with(["12345"], "Trash")

    @pytest.mark.asyncio
    async def test_download_attachment_disabled(self):
        """Test download_attachment MCP tool when feature is disabled."""
        mock_settings = MagicMock()
        mock_settings.enable_attachment_download = False

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with pytest.raises(PermissionError) as exc_info:
                await download_attachment(
                    account_name="test_account",
                    email_id="12345",
                    attachment_name="document.pdf",
                    save_path="/var/downloads/document.pdf",
                )

            assert "Attachment download is disabled" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_attachment_enabled(self):
        """Test download_attachment MCP tool when feature is enabled."""
        attachment_response = AttachmentDownloadResponse(
            email_id="12345",
            attachment_name="document.pdf",
            mime_type="application/pdf",
            size=1024,
            saved_path="/var/downloads/document.pdf",
        )

        mock_settings = MagicMock()
        mock_settings.enable_attachment_download = True

        mock_handler = AsyncMock()
        mock_handler.download_attachment.return_value = attachment_response

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
                result = await download_attachment(
                    account_name="test_account",
                    email_id="12345",
                    attachment_name="document.pdf",
                    save_path="/var/downloads/document.pdf",
                )

                assert result == attachment_response
                assert result.email_id == "12345"
                assert result.attachment_name == "document.pdf"
                assert result.mime_type == "application/pdf"
                assert result.size == 1024

                mock_handler.download_attachment.assert_called_once_with(
                    "12345", "document.pdf", "/var/downloads/document.pdf", "INBOX"
                )

    @pytest.mark.asyncio
    async def test_send_email_with_reply_headers(self):
        """Test send_email MCP tool with reply headers."""
        mock_settings = MagicMock()
        mock_settings.read_only = False

        mock_handler = AsyncMock()
        mock_handler.send_email = AsyncMock()

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
                result = await send_email(
                    account_name="test",
                    recipients=["recipient@example.com"],
                    subject="Re: Test",
                    body="Reply body",
                    in_reply_to="<original@example.com>",
                    references="<original@example.com>",
                )

                mock_handler.send_email.assert_called_once()
                call_args = mock_handler.send_email.call_args
                # Verify in_reply_to and references were passed (positions 7 and 8 after cc, bcc, html, attachments)
                assert "<original@example.com>" in str(call_args)
                assert "recipient@example.com" in result

    @pytest.mark.asyncio
    async def test_get_emails_content_includes_message_id(self):
        """Test that get_emails_content returns message_id."""
        from datetime import datetime, timezone

        mock_handler = AsyncMock()
        mock_handler.get_emails_content = AsyncMock(
            return_value=EmailContentBatchResponse(
                emails=[
                    EmailBodyResponse(
                        email_id="123",
                        message_id="<test@example.com>",
                        subject="Test",
                        sender="sender@example.com",
                        recipients=["recipient@example.com"],
                        date=datetime.now(timezone.utc),
                        body="Test body",
                        attachments=[],
                    )
                ],
                requested_count=1,
                retrieved_count=1,
                failed_ids=[],
            )
        )

        with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
            result = await get_emails_content(
                account_name="test",
                email_ids=["123"],
            )

            assert result.emails[0].message_id == "<test@example.com>"


class TestReadOnlyMode:
    @pytest.mark.asyncio
    async def test_send_email_blocked_in_read_only_mode(self):
        """Test that send_email raises PermissionError when read_only is True."""
        mock_settings = MagicMock()
        mock_settings.read_only = True

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with pytest.raises(PermissionError) as exc_info:
                await send_email(
                    account_name="test_account",
                    recipients=["recipient@example.com"],
                    subject="Test Subject",
                    body="Test Body",
                )

            assert "read-only mode" in str(exc_info.value)
            assert "create_draft" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_emails_blocked_in_read_only_mode(self):
        """Test that delete_emails raises PermissionError when read_only is True."""
        mock_settings = MagicMock()
        mock_settings.read_only = True

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with pytest.raises(PermissionError) as exc_info:
                await delete_emails(
                    account_name="test_account",
                    email_ids=["12345"],
                )

            assert "read-only mode" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_email_allowed_when_not_read_only(self):
        """Test that send_email works normally when read_only is False."""
        mock_settings = MagicMock()
        mock_settings.read_only = False

        mock_handler = AsyncMock()

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
                result = await send_email(
                    account_name="test_account",
                    recipients=["recipient@example.com"],
                    subject="Test Subject",
                    body="Test Body",
                )

                assert "Email sent successfully" in result
                mock_handler.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_emails_allowed_when_not_read_only(self):
        """Test that delete_emails works normally when read_only is False."""
        mock_settings = MagicMock()
        mock_settings.read_only = False

        mock_handler = AsyncMock()
        mock_handler.delete_emails.return_value = (["12345"], [])

        with patch("mcp_email_server.app.get_settings", return_value=mock_settings):
            with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
                result = await delete_emails(
                    account_name="test_account",
                    email_ids=["12345"],
                )

                assert "Successfully deleted" in result
                mock_handler.delete_emails.assert_called_once()


class TestCreateDraft:
    @pytest.mark.asyncio
    async def test_create_draft(self):
        """Test create_draft MCP tool."""
        mock_handler = AsyncMock()
        mock_handler.create_draft.return_value = "Drafts"

        with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
            result = await create_draft(
                account_name="test_account",
                recipients=["recipient@example.com"],
                subject="Draft Subject",
                body="Draft Body",
                cc=["cc@example.com"],
            )

            assert "Draft saved successfully" in result
            assert "Drafts" in result
            assert "recipient@example.com" in result

            mock_handler.create_draft.assert_called_once_with(
                ["recipient@example.com"],
                "Draft Subject",
                "Draft Body",
                ["cc@example.com"],
                None,
                False,
                None,
                None,
                None,
            )

    @pytest.mark.asyncio
    async def test_create_draft_allowed_in_read_only_mode(self):
        """Test that create_draft works even when read_only is True."""
        mock_handler = AsyncMock()
        mock_handler.create_draft.return_value = "Drafts"

        # create_draft does not check read_only, so we only need to mock dispatch_handler
        with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
            result = await create_draft(
                account_name="test_account",
                recipients=["recipient@example.com"],
                subject="Draft Subject",
                body="Draft Body",
            )

            assert "Draft saved successfully" in result
            mock_handler.create_draft.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_draft_with_attachments(self):
        """Test create_draft MCP tool with attachments."""
        mock_handler = AsyncMock()
        mock_handler.create_draft.return_value = "INBOX.Drafts"

        with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
            result = await create_draft(
                account_name="test_account",
                recipients=["recipient@example.com"],
                subject="Draft with attachment",
                body="See attached",
                attachments=["/tmp/file.pdf"],
            )

            assert "Draft saved successfully" in result
            assert "INBOX.Drafts" in result
            assert "1 attachment(s)" in result

    @pytest.mark.asyncio
    async def test_create_draft_with_reply_headers(self):
        """Test create_draft with reply threading headers."""
        mock_handler = AsyncMock()
        mock_handler.create_draft.return_value = "Drafts"

        with patch("mcp_email_server.app.dispatch_handler", return_value=mock_handler):
            result = await create_draft(
                account_name="test_account",
                recipients=["recipient@example.com"],
                subject="Re: Original Subject",
                body="Reply body",
                in_reply_to="<original@example.com>",
                references="<original@example.com>",
            )

            assert "Draft saved successfully" in result
            call_args = mock_handler.create_draft.call_args
            assert "<original@example.com>" in str(call_args)
